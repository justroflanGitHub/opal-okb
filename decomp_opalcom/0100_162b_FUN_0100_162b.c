
/* WARNING: Unable to track spacebase fully for stack */

void FUN_0100_162b(void)

{
  undefined1 *puVar1;
  undefined1 *puVar2;
  code *pcVar3;
  byte bVar4;
  int iVar5;
  int in_BX;
  undefined1 uVar6;
  undefined2 *puVar7;
  undefined1 *puVar8;
  undefined1 *puVar9;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  undefined1 in_CF;
  undefined2 uStack_4;
  
  while( true ) {
    FUN_0100_17a7();
    if ((bool)in_CF) {
      return;
    }
    FUN_0100_17d6();
    puVar8 = (undefined1 *)(in_BX + 4);
    puVar9 = (undefined1 *)*(undefined2 *)0x327;
    for (iVar5 = 8; iVar5 != 0; iVar5 = iVar5 + -1) {
      puVar2 = puVar9;
      puVar9 = puVar9 + 1;
      puVar1 = puVar8;
      puVar8 = puVar8 + 1;
      *puVar2 = *puVar1;
    }
    FUN_0100_180e();
    uVar6 = 1;
    *(undefined1 *)0x145 = 0xfe;
    pcVar3 = (code *)swi(0x21);
    puRam00000137 = (undefined2 *)register0x00000010;
    uRam00000139 = unaff_SS;
    (*pcVar3)();
    unaff_SS = uRam00000139;
    puVar7 = puRam00000137 + 1;
    *(undefined2 *)0x139 = *puRam00000137;
    *(undefined2 *)0x137 = *puVar7;
    uRam00000143 = 0;
    FUN_0100_1800();
    pcVar3 = (code *)swi(0x21);
    uRam00000147 = (*pcVar3)();
    bVar4 = (byte)uRam00000145;
    in_BX = CONCAT11(uVar6,(byte)uRam00000145);
    uRam00000145 = uStack_4;
    if (bVar4 == 0xfe) break;
    in_CF = bVar4 < bRam00000629;
    if (!(bool)in_CF) {
      FUN_0100_1800();
      return;
    }
    uStack_4 = 0x26b1;
    FUN_0100_17d6();
    unaff_DS = 0;
  }
  return;
}

