
void __cdecl16far FUN_2000_4617(void)

{
  char *pcVar1;
  int *piVar2;
  uint uVar3;
  code *pcVar4;
  undefined1 uVar5;
  int iVar6;
  byte *pbVar7;
  undefined2 extraout_DX;
  int in_BX;
  byte bVar8;
  undefined1 *puVar9;
  undefined4 in_EBP;
  undefined1 *puVar10;
  int iVar11;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  
  puVar10 = (undefined1 *)CONCAT22((int)((ulong)in_EBP >> 0x10),&stack0xfffe);
  *(undefined2 *)0x5446 = 0;
  *(undefined2 *)0x5444 = 1;
  do {
    uVar3 = *(uint *)0x5444;
    if (*(int *)((undefined1 *)puVar10 + -2) < (int)uVar3) {
      return;
    }
    if ((int)uVar3 < 5) {
      if (((int)uVar3 >> 0xf <= *(int *)0x39e6) &&
         (((int)uVar3 >> 0xf < *(int *)0x39e6 || (uVar3 <= *(uint *)0x39e4)))) goto LAB_2000_4656;
    }
    else {
LAB_2000_4656:
      pcVar4 = (code *)swi(0x35);
      uVar5 = (*pcVar4)();
      out(extraout_DX,uVar5);
      pcVar4 = (code *)swi(0x39);
      (*pcVar4)();
      pcVar4 = (code *)swi(0x3d);
      (*pcVar4)();
      *(undefined2 *)0x5442 = 4;
      iVar6 = *(int *)0x5444 * 0x18;
      puVar9 = (undefined1 *)puVar10;
      *(int *)(puVar9 + -4) = iVar6;
      *(int *)(puVar9 + -6) = iVar6;
      pbVar7 = (byte *)(iVar6 + 0x3c58);
      *(int *)(puVar9 + -0xc) = *(int *)(puVar9 + -4) + 0x3c58;
      *(undefined2 *)(puVar9 + -0xe) = 0x3c50;
      iVar6 = 3;
      do {
        bVar8 = (byte)((uint)in_BX >> 8);
        pcVar4 = (code *)swi(0x39);
        (*pcVar4)();
        *pbVar7 = *pbVar7 & bVar8;
        pcVar4 = (code *)swi(0x38);
        (*pcVar4)();
        pcVar4 = (code *)swi(0x3d);
        (*pcVar4)();
        pcVar4 = (code *)swi(0x39);
        (*pcVar4)();
        in_BX = *(int *)((undefined1 *)puVar10 + -0xe);
        pcVar4 = (code *)swi(0x38);
        (*pcVar4)();
        puVar10 = (undefined1 *)
                  ((ulong)puVar10 >> 0x18 | ((ulong)puVar10 & 0xff0000) >> 8 |
                   ((ulong)puVar10 & 0xff00) << 8 | (long)puVar10 << 0x18);
        pcVar4 = (code *)swi(0x39);
        (*pcVar4)();
        pcVar4 = (code *)swi(0x3d);
        (*pcVar4)();
        pbVar7 = pbVar7 + 8;
        piVar2 = (int *)((undefined1 *)puVar10 + -0xc);
        *piVar2 = *piVar2 + 8;
        piVar2 = (int *)((undefined1 *)puVar10 + -0xe);
        *piVar2 = *piVar2 + 8;
        iVar6 = iVar6 + -1;
      } while (iVar6 != 0);
      pcVar4 = (code *)swi(0x39);
      (*pcVar4)();
      *pbVar7 = *pbVar7 | (byte)((uint)in_BX >> 8);
      pcVar4 = (code *)swi(0x38);
      (*pcVar4)();
      pcVar4 = (code *)swi(0x39);
      (*pcVar4)();
      pcVar4 = (code *)swi(0x3d);
      (*pcVar4)();
      *(undefined2 *)0x5442 = 4;
      puVar9 = (undefined1 *)puVar10;
      *(int *)(puVar9 + -0x12) = *(int *)0x5444 * 0x18;
      iVar11 = 0x3be8;
      *(undefined2 *)(puVar9 + -0x18) = 3;
      iVar6 = *(int *)(puVar9 + -0x18);
      do {
        pcVar4 = (code *)swi(0x39);
        (*pcVar4)();
        pcVar4 = (code *)swi(0x38);
        (*pcVar4)();
        pcVar4 = (code *)swi(0x3d);
        (*pcVar4)();
        iVar11 = iVar11 + 8;
        iVar6 = iVar6 + -1;
      } while (iVar6 != 0);
      iVar6 = *(int *)0x5444 * 0x18;
      pcVar4 = (code *)swi(0x39);
      (*pcVar4)();
      pcVar4 = (code *)swi(0x39);
      (*pcVar4)();
      pcVar1 = (char *)(in_BX + iVar11);
      *pcVar1 = *pcVar1 + '\x01';
      if (*pcVar1 != '\0') {
        iVar11 = (int)*(uint *)0x5444 >> 0xf;
        if ((*(int *)0x39f6 <= iVar11) &&
           ((*(int *)0x39f6 < iVar11 || (*(uint *)0x39f4 <= *(uint *)0x5444)))) {
          iVar11 = (int)*(uint *)0x5444 >> 0xf;
          in_BX = *(int *)0x39f6 + *(int *)0x39fa + (uint)CARRY2(*(uint *)0x39f4,*(uint *)0x39f8);
          if ((iVar11 <= in_BX) &&
             ((iVar11 < in_BX || (*(uint *)0x5444 < *(uint *)0x39f4 + *(uint *)0x39f8)))) {
            *(int *)0x5446 = *(int *)0x5446 + 1;
            iVar11 = *(int *)0x5446 * 8;
            *(undefined2 *)(iVar11 + 0x3e28) = *(undefined2 *)0x5448;
            *(undefined2 *)(iVar11 + 0x3e2a) = *(undefined2 *)0x544a;
            *(undefined2 *)(iVar11 + 0x3e2c) = *(undefined2 *)0x544c;
            *(undefined2 *)(iVar11 + 0x3e2e) = *(undefined2 *)0x544e;
            *(undefined2 *)(iVar11 + 0x3e68) = *(undefined2 *)(iVar6 + 0x3c60);
            *(undefined2 *)(iVar11 + 0x3e6a) = *(undefined2 *)(iVar6 + 0x3c62);
            *(undefined2 *)(iVar11 + 0x3e6c) = *(undefined2 *)(iVar6 + 0x3c64);
            *(undefined2 *)(iVar11 + 0x3e6e) = *(undefined2 *)(iVar6 + 0x3c66);
            *(undefined2 *)(iVar11 + 0x3e48) = *(undefined2 *)(iVar6 + 0x3c58);
            *(undefined2 *)(iVar11 + 0x3e4a) = *(undefined2 *)(iVar6 + 0x3c5a);
            *(undefined2 *)(iVar11 + 0x3e4c) = *(undefined2 *)(iVar6 + 0x3c5c);
            *(undefined2 *)(iVar11 + 0x3e4e) = *(undefined2 *)(iVar6 + 0x3c5e);
          }
        }
      }
    }
    piVar2 = (int *)0x5444;
    iVar6 = *piVar2;
    *piVar2 = *piVar2 + 1;
    if (SCARRY2(iVar6,1)) {
      return;
    }
  } while( true );
}

