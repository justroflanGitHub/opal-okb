
/* WARNING: Stack frame is not setup normally: Input value of stackpointer is not used */
/* WARNING: This function may have set the stack pointer */

void thunk_FUN_0000_2967(void)

{
  undefined2 uVar1;
  undefined1 *puVar2;
  undefined1 *puVar3;
  char *pcVar4;
  char *pcVar5;
  char cVar6;
  code *pcVar7;
  int iVar8;
  undefined2 in_BX;
  undefined2 *puVar9;
  undefined1 *puVar10;
  undefined1 *puVar11;
  undefined1 *puVar12;
  undefined1 *puVar13;
  undefined1 *puVar14;
  undefined1 *puVar15;
  undefined1 *puVar16;
  undefined1 *puVar17;
  undefined1 *puVar18;
  undefined1 *puVar19;
  undefined2 *puVar20;
  undefined2 *puVar21;
  undefined1 *puVar22;
  undefined1 *puVar23;
  undefined1 *puVar24;
  undefined1 *puVar25;
  undefined1 *puVar26;
  undefined1 *puVar27;
  undefined1 *puVar28;
  undefined1 *puVar29;
  undefined1 *puVar30;
  undefined1 *puVar31;
  undefined1 *puVar32;
  char *pcVar33;
  int unaff_DI;
  undefined1 *puVar34;
  char *pcVar35;
  undefined2 unaff_ES;
  undefined2 unaff_CS;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  bool bVar36;
  
  puVar11 = (undefined1 *)0x100;
  pcVar7 = (code *)swi(0x21);
  (*pcVar7)();
  *(undefined2 *)0x13d = unaff_ES;
  *(undefined2 *)0x13b = in_BX;
  *(undefined2 *)(puVar11 + -2) = unaff_CS;
  pcVar7 = (code *)swi(0x21);
  (*pcVar7)();
  *(undefined2 *)0x143 = 0;
  *(undefined2 *)0x16f = unaff_CS;
  puVar12 = puVar11 + -2;
  *(undefined2 *)(puVar11 + -2) = 0x2995;
  FUN_0100_191b();
  uVar1 = *(undefined2 *)0x2c;
  puVar13 = puVar12 + -2;
  *(undefined2 *)(puVar12 + -2) = 0x299e;
  FUN_0100_1722();
  puVar34 = (undefined1 *)(unaff_DI + -1);
  iVar8 = 10;
  puVar32 = (undefined1 *)0x15f;
  cVar6 = *(char *)(unaff_DI + -2);
  if (((cVar6 == ':') || (cVar6 == '\0')) || (cVar6 == '\\')) {
    iVar8 = 9;
    puVar32 = (undefined1 *)0x160;
  }
  for (; iVar8 != 0; iVar8 = iVar8 + -1) {
    puVar3 = puVar34;
    puVar34 = puVar34 + 1;
    puVar2 = puVar32;
    puVar32 = puVar32 + 1;
    *puVar3 = *puVar2;
  }
  puVar14 = puVar13 + -2;
  *(undefined2 *)(puVar13 + -2) = 0x29bf;
  FUN_0100_185b();
  puVar15 = puVar14 + -2;
  *(undefined2 *)(puVar14 + -2) = 0x29c2;
  FUN_0100_1846();
  puVar16 = puVar15 + -2;
  *(undefined2 *)(puVar15 + -2) = 0x29cb;
  FUN_0100_191b();
  uVar1 = *(undefined2 *)0x2c;
  pcVar35 = puVar34 + 4;
  puVar17 = puVar16 + -2;
  *(undefined2 *)(puVar16 + -2) = 0x29d7;
  FUN_0100_1722();
  iVar8 = 0x49;
  do {
    if (iVar8 == 0) break;
    iVar8 = iVar8 + -1;
    pcVar4 = pcVar35;
    pcVar35 = pcVar35 + -1;
  } while (*pcVar4 != '\\');
  pcVar35 = pcVar35 + 2;
  *(char **)(puVar17 + -2) = pcVar35;
  pcVar33 = (char *)0x156;
  for (iVar8 = 9; iVar8 != 0; iVar8 = iVar8 + -1) {
    pcVar5 = pcVar35;
    pcVar35 = pcVar35 + 1;
    pcVar4 = pcVar33;
    pcVar33 = pcVar33 + 1;
    *pcVar5 = *pcVar4;
  }
  puVar18 = puVar17 + -4;
  *(undefined2 *)(puVar17 + -4) = 0x29f1;
  FUN_0100_18ad();
  puVar19 = puVar18 + -2;
  *(undefined2 *)(puVar18 + -2) = 0x29f4;
  FUN_0100_1846();
  puVar20 = (undefined2 *)(puVar19 + -2);
  *(undefined2 *)(puVar19 + -2) = 0x29fb;
  thunk_FUN_0100_1761();
  puVar34 = (undefined1 *)*puVar20;
  puVar21 = puVar20 + 1;
  puVar32 = (undefined1 *)0x14a;
  for (iVar8 = 0xb; iVar8 != 0; iVar8 = iVar8 + -1) {
    puVar3 = puVar34;
    puVar34 = puVar34 + 1;
    puVar2 = puVar32;
    puVar32 = puVar32 + 1;
    *puVar3 = *puVar2;
  }
  pcVar7 = (code *)swi(0x21);
  (*pcVar7)();
  puVar22 = (undefined1 *)((int)puVar21 + -2);
  *(undefined2 *)((int)puVar21 + -2) = 0x2a10;
  FUN_0100_1800();
  puVar23 = puVar22 + -2;
  *(undefined2 *)(puVar22 + -2) = 0x2a13;
  FUN_0100_1846();
  puVar24 = puVar23 + -2;
  *(undefined2 *)(puVar23 + -2) = 0x2a1e;
  FUN_0100_1751();
  puVar25 = puVar24 + -2;
  *(undefined2 *)(puVar24 + -2) = 0x2a21;
  thunk_FUN_0100_1761();
  puVar26 = puVar25 + -2;
  *(undefined2 *)(puVar25 + -2) = 0x2a24;
  FUN_0100_1846();
  puVar27 = puVar26 + -2;
  *(undefined2 *)(puVar26 + -2) = 0x2a2c;
  FUN_0100_191b();
  puVar28 = puVar27 + -2;
  *(undefined2 *)(puVar27 + -2) = 0x2a34;
  FUN_0100_191b();
  puVar29 = puVar28 + -2;
  *(undefined2 *)(puVar28 + -2) = 0x2a3c;
  FUN_0100_191b();
  puVar30 = puVar29 + -2;
  *(undefined2 *)(puVar29 + -2) = 0x2a44;
  FUN_0100_191b();
  uVar1 = *(undefined2 *)0x2c;
  pcVar35 = puVar34 + 4;
  puVar31 = puVar30 + -2;
  *(undefined2 *)(puVar30 + -2) = 0x2a50;
  FUN_0100_1722();
  iVar8 = 0x49;
  do {
    if (iVar8 == 0) break;
    iVar8 = iVar8 + -1;
    pcVar4 = pcVar35;
    pcVar35 = pcVar35 + -1;
  } while (*pcVar4 != '\\');
  pcVar35 = pcVar35 + 2;
  *(undefined2 *)0x327 = pcVar35;
  pcVar33 = (char *)0x1b6a;
  for (iVar8 = 0xd; iVar8 != 0; iVar8 = iVar8 + -1) {
    pcVar5 = pcVar35;
    pcVar35 = pcVar35 + 1;
    pcVar4 = pcVar33;
    pcVar33 = pcVar33 + 1;
    *pcVar5 = *pcVar4;
  }
  bVar36 = true;
  pcVar7 = (code *)swi(0x21);
  (*pcVar7)();
  if (!bVar36) {
    puVar9 = (undefined2 *)(puVar31 + -2);
    puVar31 = puVar31 + -2;
    *puVar9 = (code *)FUN_0000_282d;
    FUN_0100_16a3();
  }
  do {
    *(undefined1 *)0x149 = 1;
    puVar10 = puVar31 + -2;
    *(undefined2 *)(puVar31 + -2) = 0x2835;
    FUN_0100_1781();
    puVar31 = puVar10 + -2;
    *(undefined2 *)(puVar10 + -2) = 0x2838;
    FUN_0100_1846();
    unaff_DS = (undefined2)((ulong)*(undefined4 *)0x13b >> 0x10);
    pcVar7 = (code *)swi(0x21);
    (*pcVar7)();
    pcVar7 = (code *)swi(0x21);
    (*pcVar7)();
    if (*(int *)0x143 == 0) {
      return;
    }
    *(undefined2 *)0x143 = 0;
  } while (*(char *)0x149 != '\x01');
  return;
}

