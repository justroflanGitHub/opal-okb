
/* WARNING: Unable to track spacebase fully for stack */

void FUN_0100_16a3(undefined2 param_1,undefined2 param_2,undefined2 param_3)

{
  undefined1 *puVar1;
  undefined1 *puVar2;
  code *pcVar3;
  int iVar4;
  int in_BX;
  undefined2 *puVar5;
  undefined1 *puVar6;
  undefined1 *puVar7;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  undefined1 uVar8;
  
  while( true ) {
    if ((byte)in_BX == 0xfe) {
      return;
    }
    uVar8 = (byte)in_BX < *(byte *)0x629;
    if (!(bool)uVar8) break;
    FUN_0100_17d6();
    FUN_0100_17a7();
    if ((bool)uVar8) {
      return;
    }
    param_1 = 0x2637;
    FUN_0100_17d6();
    puVar6 = (undefined1 *)(in_BX + 4);
    puVar7 = (undefined1 *)*(undefined2 *)0x327;
    for (iVar4 = 8; iVar4 != 0; iVar4 = iVar4 + -1) {
      puVar2 = puVar7;
      puVar7 = puVar7 + 1;
      puVar1 = puVar6;
      puVar6 = puVar6 + 1;
      *puVar2 = *puVar1;
    }
    param_2 = 0x2648;
    FUN_0100_180e();
    uVar8 = 1;
    param_3 = *(undefined2 *)0x145;
    *(undefined1 *)0x145 = 0xfe;
    param_2 = *(undefined2 *)0x137;
    param_1 = *(undefined2 *)0x139;
    puRam00000137 = &param_1;
    pcVar3 = (code *)swi(0x21);
    uRam00000139 = unaff_SS;
    (*pcVar3)();
    unaff_SS = uRam00000139;
    puVar5 = puRam00000137 + 1;
    *(undefined2 *)0x139 = *puRam00000137;
    *(undefined2 *)0x137 = *puVar5;
    uRam00000143 = 0;
    FUN_0100_1800();
    pcVar3 = (code *)swi(0x21);
    uRam00000147 = (*pcVar3)();
    in_BX = CONCAT11(uVar8,(undefined1)uRam00000145);
    uRam00000145 = 0x26b1;
    unaff_DS = 0;
  }
  FUN_0100_1800();
  return;
}

